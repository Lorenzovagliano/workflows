import datetime
import re
import xml.etree.ElementTree as ET

from common.parsing.parser import IParser, ObjectExtractor
from common.parsing.xml_extractors import (
    AttributeExtractor,
    CustomExtractor,
    TextExtractor,
)


class SpringerParser(IParser):
    def __init__(self) -> None:

        article_type_mapping = {
            "OriginalPaper": "article",
            "ReviewPaper": "review",
            "BriefCommunication": "article",
            "EditorialNotes": "editorial",
            "BookReview": "review",
            "ContinuingEducation": "other",
            "Interview": "other",
            "Letter": "other",
            "Erratum": "erratum",
            "Legacy": "other",
            "Abstract": "other",
            "Report": "other",
            "Announcement": "other",
            "News": "other",
            "Events": "other",
            "Acknowledgments": "other",
            "MediaReport": "other",
            "BibliographicalNote": "other",
            "ProductNotes": "other",
            "Unknown": "other",
        }

        extractors = [
            AttributeExtractor(
                "journal_doctype",
                "./Journal/Volume/Issue/Article/ArticleInfo",
                "ArticleType",
                extra_function=lambda x: article_type_mapping[x],
            ),
            TextExtractor(
                "dois", "./Journal/Volume/Issue/Article/ArticleInfo/ArticleDOI"
            ),
            CustomExtractor("arxiv_eprints", self._get_arxiv_eprints),
            CustomExtractor("page_nr", self._get_page_nrs),
            CustomExtractor("abstract", self._get_abstract),
            TextExtractor(
                "title",
                "./Journal/Volume/Issue/Article/ArticleInfo/ArticleTitle",
            ),
            CustomExtractor("authors", self._get_authors),
            TextExtractor(
                "collaborations",
                "./Journal/Volume/Issue/Article/ArticleHeader/AuthorGroup/InstitutionalAuthor/InstitutionalAuthorName",
                False,
                extra_function=lambda x: [x],
            ),
            TextExtractor(
                "journal_title",
                "./Journal/JournalInfo/JournalTitle",
                extra_function=lambda s: s.lstrip("The "),
            ),
            TextExtractor(
                "journal_issue", "./Journal/Volume/Issue/IssueInfo/IssueIDStart"
            ),
            TextExtractor(
                "journal_volume", "./Journal/Volume/VolumeInfo/VolumeIDStart"
            ),
            AttributeExtractor("journal_artid", "./Journal/Volume/Issue/Article", "ID"),
            TextExtractor(
                "journal_fpage",
                "./Journal/Volume/Issue/Article/ArticleInfo/ArticleFirstPage",
            ),
            TextExtractor(
                "journal_lpage",
                "./Journal/Volume/Issue/Article/ArticleInfo/ArticleLastPage",
            ),
            TextExtractor(
                "journal_year",
                "./Journal/Volume/Issue/Article/ArticleInfo/*/OnlineDate/Year",
                extra_function=lambda x: int(x),
            ),
            CustomExtractor("date_published", self._get_published_date),
            TextExtractor(
                "copyright_holder",
                "./Journal/Volume/Issue/Article/ArticleInfo/ArticleCopyright/CopyrightHolderName",
            ),
            TextExtractor(
                "copyright_year",
                "./Journal/Volume/Issue/Article/ArticleInfo/ArticleCopyright/CopyrightYear",
            ),
            TextExtractor(
                "copyright_statement",
                "./Journal/Volume/Issue/Article/ArticleInfo/ArticleCopyright/copyright-statement",
                False,
            ),
            CustomExtractor("license", self._get_license),
            TextExtractor(
                "collections",
                "./Journal/JournalInfo/JournalTitle",
                extra_function=lambda x: [x.lstrip("The ")],
            ),
        ]
        super().__init__(extractors)

    def _get_abstract(self, article: ET.Element):
        paragraph = article.find(
            "./Journal/Volume/Issue/Article/ArticleHeader/Abstract/Para"
        )

        text_to_skip_arrays = [
            [child_text for child_text in child.itertext()] for child in paragraph
        ]
        text_to_skip_flatten = [
            item for sublist in text_to_skip_arrays for item in sublist
        ]

        abstract = " ".join(
            [text for text in paragraph.itertext() if text not in text_to_skip_flatten]
        )

        return re.sub("\\s+", " ", abstract)

    def _get_arxiv_eprints(self, article: ET.Element):
        arxiv_eprints = []
        for arxiv in article.findall(
            "./Journal/Volume/Issue/Article/ArticleInfo/ArticleExternalID[@Type='arXiv']"
        ):
            arxiv_eprints.append({"value": arxiv.text})
        return arxiv_eprints

    def _clean_aff(self, article: ET.Element):
        org_div_node = article.find("./OrgDivision")
        org_name_node = article.find("./OrgName")
        street_node = article.find("./OrgAddress/Street")
        city_node = article.find("./OrgAddress/City")
        state_node = article.find("./OrgAddress/State")
        postcode_node = article.find("./OrgAddress/Postcode")
        country_node = article.find("./OrgAddress/Country")

        result = [
            node.text
            for node in [
                org_div_node,
                org_name_node,
                street_node,
                city_node,
                state_node,
                postcode_node,
                country_node,
            ]
            if node is not None
        ]

        return ", ".join(result), org_name_node.text, country_node.text

    def _get_published_date(self, article: ET.Element):
        year = article.find(
            "./Journal/Volume/Issue/Article/ArticleInfo/*/OnlineDate/Year"
        ).text
        month = article.find(
            "./Journal/Volume/Issue/Article/ArticleInfo/*/OnlineDate/Month"
        ).text
        day = article.find(
            "./Journal/Volume/Issue/Article/ArticleInfo/*/OnlineDate/Day"
        ).text
        return datetime.date(day=int(day), month=int(month), year=int(year)).isoformat()

    def _get_affiliations(self, author_group: ET.Element, contrib: ET.Element):
        affiliations = []
        referred_id = contrib.get("AffiliationIDS")

        if not referred_id:
            return affiliations

        for ref in referred_id.split():
            cleaned_aff = self._clean_aff(
                author_group.find(f"./Affiliation[@ID='{ref}']")
            )
            if cleaned_aff not in affiliations:
                affiliations.append(cleaned_aff)

        mapped_affiliations = [
            {"value": aff, "organization": org, "country": country}
            for aff, org, country, in affiliations
        ]

        return mapped_affiliations

    def _get_authors(self, article: ET.Element):
        authors = []
        for contrib in article.findall(
            "./Journal/Volume/Issue/Article/ArticleHeader/AuthorGroup/Author"
        ):
            author = ObjectExtractor(
                None,
                [
                    TextExtractor("surname", "./AuthorName/FamilyName"),
                    TextExtractor("given_names", "./AuthorName/GivenName"),
                    TextExtractor("email", "./Contact/Email", False),
                ],
            ).extract(contrib)
            author["affiliations"] = self._get_affiliations(
                article.find(
                    "./Journal/Volume/Issue/Article/ArticleHeader/AuthorGroup"
                ),
                contrib,
            )

            authors.append(author)

        return authors

    def _get_page_nrs(self, article: ET.Element):
        first_page_node = article.find(
            "./Journal/Volume/Issue/Article/ArticleInfo/ArticleFirstPage"
        )
        last_page_node = article.find(
            "./Journal/Volume/Issue/Article/ArticleInfo/ArticleLastPage"
        )
        return (
            [int(last_page_node.text) - int(first_page_node.text) + 1]
            if first_page_node is not None and last_page_node is not None
            else []
        )

    def _get_license(self, article: ET.Element):
        license_node = article.find(
            "./Journal/Volume/Issue/Article/ArticleInfo/ArticleCopyright/License"
        )
        version_node = article.find(
            "./Journal/Volume/Issue/Article/ArticleInfo/ArticleCopyright/License"
        )
        text = "https://creativecommons.org/licenses/"

        if license_node is not None:
            license_type = license_node.get("SubType")
            version = version_node.get("Version")
            license_type = license_type.lower().lstrip("cc ").replace(" ", "-")
            return [
                {
                    "license": "CC-" + license_type.upper() + "-" + version,
                    "url": f"{text}/{license_type}/{version}",
                }
            ]

        return [
            {
                "license": "CC-BY-3.0",
                "url": "https://creativecommons.org/licenses/by/3.0",
            }
        ]