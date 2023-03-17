import os

from common.parsing.xml_extractors import RequiredFieldNotFoundExtractionError
from common.utils import parse_without_names_spaces
from oup.parser import OUPParser
from pytest import fixture, raises


@fixture(scope="module")
def parser():
    return OUPParser()


@fixture
def valid_articles(shared_datadir):
    articles = []
    valid_article_names = ["ptac108.xml", "ptac113.xml", "ptac120.xml", "ptab170.xml"]
    for filename in sorted(valid_article_names):
        with open(os.path.join(shared_datadir, filename)) as file:
            articles.append(parse_without_names_spaces(file.read()))
    yield articles


@fixture()
def parsed_articles(parser, valid_articles):
    yield [parser._publisher_specific_parsing(article) for article in valid_articles]


def test_dois(parsed_articles):
    dois = [
        "10.1093/ptep/ptac108",
        "10.1093/ptep/ptac120",
        "10.1093/ptep/ptac113",
        "10.1093/ptep/ptab170",
    ]
    dois_parsed_article = [article["dois"][0] for article in parsed_articles]
    assert set(dois) == set(dois_parsed_article)


def test_no_doi_article(shared_datadir, parser):
    article_name = "ptac108_without_doi.xml"
    with open(shared_datadir / article_name) as file:
        content = parse_without_names_spaces(file.read())
        with raises(RequiredFieldNotFoundExtractionError):
            parser._publisher_specific_parsing(content)


def test_no_doi_value_article(shared_datadir, parser):
    article_name = "ptac108_without_doi_value.xml"
    with open(shared_datadir / article_name) as file:
        content = parse_without_names_spaces(file.read())
        with raises(RequiredFieldNotFoundExtractionError):
            parser._publisher_specific_parsing(content)


def test_journal_doc_types(parsed_articles):
    doc_types = sorted(["article", "article", "article", "other"])
    parsed_articles_types = sorted(
        [article["journal_doctype"] for article in parsed_articles]
    )
    assert parsed_articles_types == doc_types


def test_no_doc_type_article(shared_datadir, parser):
    article_name = "ptac113_without_journal_doc_type.xml"
    with open(shared_datadir / article_name) as file:
        content = parse_without_names_spaces(file.read())
        article = parser._publisher_specific_parsing(content)
        assert "journal_doctype" not in article


@fixture
def other_doc_type_article(shared_datadir, parser):
    article_name = "ptac113_other_journal_doc_type.xml"
    with open(shared_datadir / article_name) as file:
        content = parse_without_names_spaces(file.read())
        yield parser._publisher_specific_parsing(content)


def test_other_journal_doc_types(other_doc_type_article):
    assert "other" == other_doc_type_article["journal_doctype"]
