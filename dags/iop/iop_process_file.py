import base64
import xml.etree.ElementTree as ET

import pendulum
from airflow.decorators import dag, task
from common.cleanup import (
    convert_html_italics_to_latex,
    convert_html_subscripts_to_latex,
    replace_cdata_format,
)
from common.enhancer import Enhancer
from common.enricher import Enricher
from common.exceptions import EmptyOutputFromPreviousTask
from common.scoap3_s3 import Scoap3Repository
from common.utils import create_or_update_article, upload_json_to_s3
from inspire_utils.record import get_value
from iop.parser import IOPParser
from iop.repository import IOPRepository
from structlog import get_logger

logger = get_logger()


def process_xml(input, italics=True):
    input = convert_html_subscripts_to_latex(input)
    if italics:
        input = convert_html_italics_to_latex(input)
    input = replace_cdata_format(input)
    return input


def convert_xml_to_et_tree(input):
    try:
        xml = process_xml(input)
        xml = ET.fromstring(xml)

    except (ET.ParseError, TypeError):
        xml = process_xml(input, italics=False)
        xml = ET.fromstring(xml)

    return xml


def iop_parse_file(**kwargs):
    if "params" not in kwargs or "file" not in kwargs["params"]:
        raise Exception("There was no 'file' parameter. Exiting run.")
    encoded_xml = kwargs["params"]["file"]
    file_name = kwargs["params"]["file_name"]
    xml_bytes = base64.b64decode(encoded_xml)
    if isinstance(xml_bytes, bytes):
        xml_bytes = xml_bytes.decode("utf-8")
    xml = convert_xml_to_et_tree(xml_bytes)

    parser = IOPParser(file_path=file_name)
    parsed = parser.parse(xml)

    return parsed


def iop_enhance_file(parsed_file):
    return Enhancer()("IOP", parsed_file)


def iop_enrich_file(enhanced_file):
    return Enricher()(enhanced_file)


@dag(schedule=None, start_date=pendulum.today("UTC").add(days=-1))
def iop_process_file():
    s3_client = IOPRepository()

    @task()
    def parse_file(**kwargs):
        return iop_parse_file(**kwargs)

    @task()
    def enhance_file(parsed_file):
        if not parsed_file:
            raise EmptyOutputFromPreviousTask("parse_file")
        return iop_enhance_file(parsed_file)

    @task()
    def enrich_file(enhanced_file):
        if not enhanced_file:
            raise EmptyOutputFromPreviousTask("enhance_file")
        return iop_enrich_file(enhanced_file)

    @task()
    def populate_files(parsed_file):
        if "files" not in parsed_file:
            logger.info("No files to populate")
            return parsed_file

        logger.info("Populating files", files=parsed_file["files"])

        s3_client_bucket = IOPRepository().bucket
        s3_scoap3_client = Scoap3Repository()
        doi = get_value(parsed_file, "dois.value[0]")
        files = s3_scoap3_client.copy_files(
            s3_client_bucket, parsed_file["files"], prefix=doi
        )
        parsed_file["files"] = files
        logger.info("Files populated", files=parsed_file["files"])
        return parsed_file

    @task()
    def create_or_update(enriched_file):
        create_or_update_article(enriched_file)

    @task()
    def save_to_s3(enriched_file):
        upload_json_to_s3(json_record=enriched_file, repo=s3_client)

    parsed_file = parse_file()
    enhanced_file = enhance_file(parsed_file)
    enhanced_file_with_files = populate_files(enhanced_file)
    enriched_file = enrich_file(enhanced_file_with_files)
    save_to_s3(enriched_file=enriched_file)
    create_or_update(enriched_file)


dag_taskflow = iop_process_file()
