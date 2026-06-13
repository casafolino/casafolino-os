import gzip
import json
import logging
from xml.etree import ElementTree

import requests

from odoo.exceptions import ValidationError

from odoo.addons.sale_amazon import utils as amazon_utils


_logger = logging.getLogger(__name__)
_original_get_feed_document = amazon_utils.get_feed_document


def _json_report_to_xml(report):
    root = ElementTree.Element("ProcessingReport")
    summary = ElementTree.SubElement(root, "ProcessingSummary")
    report_summary = report.get("summary", {})
    errors = int(report_summary.get("errors") or report_summary.get("messagesInvalid") or 0)
    ElementTree.SubElement(summary, "MessagesWithError").text = str(errors)

    for issue in report.get("issues", []):
        severity = issue.get("severity") or issue.get("issueSeverity")
        if severity and severity.upper() not in {"ERROR", "FATAL"}:
            continue
        result = ElementTree.SubElement(root, "Result")
        ElementTree.SubElement(result, "ResultCode").text = "Error"
        ElementTree.SubElement(result, "ResultDescription").text = (
            issue.get("message") or issue.get("description") or json.dumps(issue)
        )
        sku = issue.get("sku")
        if sku:
            additional = ElementTree.SubElement(result, "AdditionalInfo")
            ElementTree.SubElement(additional, "SKU").text = sku

    return root


def _get_feed_document(account, document_ref):
    response_content = amazon_utils.make_sp_api_request(
        account, "getFeedDocument", path_parameter=document_ref
    )
    document_url = response_content["url"]
    try:
        response = requests.get(document_url, timeout=60)
        response.raise_for_status()
        content = response.content
        if response_content.get("compressionAlgorithm") == "GZIP":
            content = gzip.decompress(content)
        stripped = content.lstrip()
        if stripped.startswith(b"{"):
            return _json_report_to_xml(json.loads(content.decode("utf-8")))
        return ElementTree.fromstring(content).find("Message/ProcessingReport")
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        _logger.exception(
            "Could not establish the connection to download the feed document at %s", document_url
        )
        raise ValidationError(account.env._("Could not establish the connection to the API."))
    except requests.exceptions.HTTPError:
        _logger.exception(
            "Invalid API request while downloading the feed document at %s", document_url
        )
        raise ValidationError(account.env._("The communication with the API failed."))
    except (ElementTree.ParseError, gzip.BadGzipFile, json.JSONDecodeError, UnicodeDecodeError):
        _logger.exception("Could not parse the feed document at %s", document_url)
        raise ValidationError(account.env._("Could not process the feed document send by Amazon."))


amazon_utils.get_feed_document = _get_feed_document
