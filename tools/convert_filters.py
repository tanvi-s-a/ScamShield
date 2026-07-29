from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


COSMETIC_BLOCK = "##"
COSMETIC_EXCEPTION = "#@#"

HOSTNAME_PATTERN = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)

RESOURCE_TYPE_MAP = {
    "document": "main_frame",
    "subdocument": "sub_frame",
    "stylesheet": "stylesheet",
    "script": "script",
    "image": "image",
    "font": "font",
    "media": "media",
    "object": "object",
    "xmlhttprequest": "xmlhttprequest",
    "xhr": "xmlhttprequest",
    "ping": "ping",
    "websocket": "websocket",
    "other": "other",
}

UNSUPPORTED_COSMETIC_MARKERS = (
    "##+js(",
    "#$#",
    "#%#",
    ":has-text(",
    ":matches-css(",
    ":matches-path(",
    ":min-text-length(",
    ":others(",
    ":remove(",
    ":style(",
    ":upward(",
    ":watch-attr(",
)


def normalize_domain(value: str) -> str | None:
    """Normalize and validate an ordinary hostname."""
    domain = value.strip().lower().rstrip(".").lstrip(".")

    if domain.startswith("www."):
        domain = domain[4:]

    if not HOSTNAME_PATTERN.fullmatch(domain):
        return None

    return domain


def is_safe_css_selector(selector: str) -> bool:
    """
    Perform conservative checks.

    The browser still performs the final selector validation when
    document.querySelectorAll() runs.
    """
    selector = selector.strip()

    if not selector:
        return False

    if any(marker in selector for marker in UNSUPPORTED_COSMETIC_MARKERS):
        return False

    # HTML filtering syntax is not an ordinary CSS selector.
    if selector.startswith("^"):
        return False

    return True


def parse_domain_option(
    value: str,
) -> tuple[list[str], list[str]]:
    """
    Convert:
        domain=example.com|example.org|~excluded.com
    into included and excluded initiator domains.
    """
    included: list[str] = []
    excluded: list[str] = []

    for item in value.split("|"):
        item = item.strip()

        if not item:
            continue

        is_excluded = item.startswith("~")
        candidate = item[1:] if is_excluded else item
        domain = normalize_domain(candidate)

        if domain is None:
            continue

        if is_excluded:
            excluded.append(domain)
        else:
            included.append(domain)

    return sorted(set(included)), sorted(set(excluded))


def parse_network_options(
    option_text: str,
) -> dict[str, Any] | None:
    """
    Parse a useful subset of EasyList/uBO network options.

    Returns None when an unsupported option could substantially
    change the meaning of the rule.
    """
    included_types: list[str] = []
    excluded_types: list[str] = []
    initiator_domains: list[str] = []
    excluded_initiator_domains: list[str] = []
    domain_type: str | None = None

    harmless_ignored_options = {
        "important",
        "match-case",
    }

    for raw_option in option_text.split(","):
        option = raw_option.strip().lower()

        if not option:
            continue

        if option in RESOURCE_TYPE_MAP:
            included_types.append(RESOURCE_TYPE_MAP[option])
            continue

        if option.startswith("~"):
            positive_name = option[1:]

            if positive_name in RESOURCE_TYPE_MAP:
                excluded_types.append(
                    RESOURCE_TYPE_MAP[positive_name]
                )
                continue

            if positive_name == "third-party":
                domain_type = "firstParty"
                continue

        if option in {"third-party", "3p"}:
            domain_type = "thirdParty"
            continue

        if option in {"first-party", "1p"}:
            domain_type = "firstParty"
            continue

        if option.startswith("domain="):
            included, excluded = parse_domain_option(
                option.removeprefix("domain=")
            )
            initiator_domains.extend(included)
            excluded_initiator_domains.extend(excluded)
            continue

        if option in harmless_ignored_options:
            continue

        # These need behavior our converter does not implement.
        unsupported_prefixes = (
            "redirect",
            "redirect-rule",
            "removeparam",
            "replace",
            "urltransform",
            "csp",
            "permissions",
            "header",
            "ipaddress",
            "to=",
            "from=",
            "denyallow=",
            "method=",
        )

        if option.startswith(unsupported_prefixes):
            return None

        # Unknown modifiers are skipped conservatively.
        return None

    condition: dict[str, Any] = {}

    if included_types:
        condition["resourceTypes"] = sorted(set(included_types))

    if excluded_types:
        condition["excludedResourceTypes"] = sorted(
            set(excluded_types)
        )

    if initiator_domains:
        condition["initiatorDomains"] = sorted(
            set(initiator_domains)
        )

    if excluded_initiator_domains:
        condition["excludedInitiatorDomains"] = sorted(
            set(excluded_initiator_domains)
        )

    if domain_type is not None:
        condition["domainType"] = domain_type

    return condition


def parse_network_rule(
    line: str,
) -> tuple[str, dict[str, Any]] | None:
    """
    Convert supported EasyList/uBlock-style network filters.

    Examples:
        ||doubleclick.net^
        ||example.com^$script,image
        ||example.com/ads/
        ||example.com/banner*.js$script
        /advertisements/
        *-advertisement.*
        @@||example.com^$image

    Simple hostname rules use requestDomains. Other basic patterns use
    Chrome's urlFilter syntax.
    """

    action_type = "block"
    body = line.strip()

    if body.startswith("@@"):
        action_type = "allow"
        body = body[2:]

    if not body:
        return None

    # Modifier-only rules do not contain a usable URL pattern.
    if body.startswith("$"):
        return None

    # Skip clear regular-expression filters for now. They require
    # regexFilter rather than urlFilter.
    if (
        body.startswith("/^")
        or body.startswith(r"/\/")
        or body.startswith(r"/\.")
    ):
        return None

    if "$" in body:
        pattern, option_text = body.rsplit("$", 1)
    else:
        pattern = body
        option_text = ""

    pattern = pattern.strip()
    option_text = option_text.strip()

    if not pattern:
        return None

    option_condition = parse_network_options(option_text)

    if option_condition is None:
        return None

    condition: dict[str, Any] = {
        **option_condition,
    }

    # Optimize an exact plain-hostname rule:
    #
    #     ||example.com^
    #
    # into requestDomains rather than urlFilter.
    if pattern.startswith("||") and pattern.endswith("^"):
        domain_text = pattern[2:-1]

        if not any(
            character in domain_text
            for character in "/*|:^?="
        ):
            domain = normalize_domain(domain_text)

            if domain is not None:
                condition["requestDomains"] = [domain]
                return action_type, condition

    # Chrome limits urlFilter strings to 2,000 characters.
    if len(pattern) > 2000:
        return None

    # Reject cosmetic and unsupported extended-filter syntax.
    if (
        "##" in pattern
        or "#@#" in pattern
        or "#$#" in pattern
        or "#%#" in pattern
        or "##+js(" in pattern
    ):
        return None

    # Basic EasyList patterns such as ||, |, *, and ^ are compatible
    # with Chrome DNR urlFilter syntax.
    condition["urlFilter"] = pattern

    return action_type, condition


def parse_cosmetic_rule(
    line: str,
) -> tuple[str, list[dict[str, str]]] | None:
    """
    Returns:
        ("block" or "exception", cosmetic rules)
    """
    if COSMETIC_EXCEPTION in line:
        separator = COSMETIC_EXCEPTION
        action = "exception"
    elif COSMETIC_BLOCK in line:
        separator = COSMETIC_BLOCK
        action = "block"
    else:
        return None

    site_text, selector = line.split(separator, 1)
    site_text = site_text.strip()
    selector = selector.strip()

    if not is_safe_css_selector(selector):
        return None

    if not site_text or site_text == "*":
        return action, [{
            "site": "*",
            "selector": selector,
        }]

    rules: list[dict[str, str]] = []

    for raw_site in site_text.split(","):
        raw_site = raw_site.strip()

        # Negated hostnames require a richer rule representation.
        if not raw_site or raw_site.startswith("~"):
            continue

        site = normalize_domain(raw_site)

        if site is not None:
            rules.append({
                "site": site,
                "selector": selector,
            })

    if not rules:
        return None

    return action, rules


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    )

def find_source_files(source_path: Path) -> list[Path]:
    """
    Accept either one .txt file or a directory containing .txt files.
    """

    if source_path.is_file():
        return [source_path]

    if source_path.is_dir():
        files = sorted(
            path
            for path in source_path.rglob("*.txt")
            if path.is_file()
        )

        if not files:
            raise SystemExit(
                f"No .txt filter files found in: {source_path}"
            )

        return files

    raise SystemExit(
        f"Input file or directory does not exist: {source_path}"
    )

def convert_filter_files(
    source_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    network_entries: list[tuple[str, dict[str, Any]]] = []
    cosmetic_rules: list[dict[str, str]] = []
    cosmetic_exceptions: set[tuple[str, str]] = set()

    statistics = {
        "sourceFilesProcessed": 0,
        "totalLines": 0,
        "commentsOrBlankLines": 0,
        "networkBlockRulesConverted": 0,
        "networkAllowRulesConverted": 0,
        "cosmeticRulesConverted": 0,
        "cosmeticExceptionsApplied": 0,
        "duplicatesRemoved": 0,
        "unsupportedRulesSkipped": 0,
    }

    source_files = find_source_files(source_path)
    statistics["sourceFilesProcessed"] = len(source_files)

    for source_file in source_files:
        lines = source_file.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        for raw_line in lines:
            statistics["totalLines"] += 1
            line = raw_line.strip()

            if (
                not line
                or line.startswith("!")
                or line.startswith("[")
            ):
                statistics["commentsOrBlankLines"] += 1
                continue

            cosmetic_result = parse_cosmetic_rule(line)

            if cosmetic_result is not None:
                action, parsed_rules = cosmetic_result

                if action == "block":
                    cosmetic_rules.extend(parsed_rules)
                    statistics["cosmeticRulesConverted"] += len(
                        parsed_rules
                    )
                else:
                    for rule in parsed_rules:
                        cosmetic_exceptions.add(
                            (rule["site"], rule["selector"])
                        )

                continue

            network_result = parse_network_rule(line)

            if network_result is not None:
                action, condition = network_result
                network_entries.append((action, condition))

                if action == "allow":
                    statistics[
                        "networkAllowRulesConverted"
                    ] += 1
                else:
                    statistics[
                        "networkBlockRulesConverted"
                    ] += 1

                continue

            statistics["unsupportedRulesSkipped"] += 1

    # Remove exact cosmetic rules cancelled by exact exceptions.
    filtered_cosmetic_rules: list[dict[str, str]] = []

    for rule in cosmetic_rules:
        key = (rule["site"], rule["selector"])

        if key in cosmetic_exceptions:
            statistics["cosmeticExceptionsApplied"] += 1
            continue

        filtered_cosmetic_rules.append(rule)

    # Deduplicate cosmetic rules.
    unique_cosmetic: dict[
        tuple[str, str],
        dict[str, str],
    ] = {}

    for rule in filtered_cosmetic_rules:
        key = (rule["site"], rule["selector"])

        if key in unique_cosmetic:
            statistics["duplicatesRemoved"] += 1

        unique_cosmetic[key] = rule

    # Deduplicate network rules.
    unique_network: dict[
        tuple[str, str],
        tuple[str, dict[str, Any]],
    ] = {}

    for action, condition in network_entries:
        key = (action, canonical_json(condition))

        if key in unique_network:
            statistics["duplicatesRemoved"] += 1

        unique_network[key] = (action, condition)

    sorted_network = sorted(
        unique_network.values(),
        key=lambda entry: (
            entry[0],
            canonical_json(entry[1]),
        ),
    )

    dnr_rules: list[dict[str, Any]] = []

    for rule_id, (action, condition) in enumerate(
        sorted_network,
        start=1,
    ):
        dnr_rules.append({
            "id": rule_id,
            # Allow rules outrank ordinary block rules.
            "priority": 2 if action == "allow" else 1,
            "action": {
                "type": action,
            },
            "condition": condition,
        })

    sorted_cosmetic = sorted(
        unique_cosmetic.values(),
        key=lambda rule: (
            rule["site"],
            rule["selector"],
        ),
    )

    filters_output = {
        "metadata": {
            "formatVersion": 2,
            "sourceFile": source_path.name,
            "description": (
                "Frozen filter snapshot converted for ScamShield"
            ),
            "statistics": statistics,
        },
        "cosmeticRules": sorted_cosmetic,
    }

    return filters_output, dnr_rules


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a supported subset of EasyList/uBlock-style "
            "filters into ScamShield cosmetic and Chrome MV3 rules."
        )
    )

    parser.add_argument(
        "source",
        type=Path,
        help="Input filter-list file or directory of .txt files",
    )

    parser.add_argument(
        "--filters-output",
        type=Path,
        default=Path("filters.json"),
        help="Cosmetic JSON output; default: filters.json",
    )

    parser.add_argument(
        "--rules-output",
        type=Path,
        default=Path("rules.json"),
        help="Chrome DNR output; default: rules.json",
    )

    args = parser.parse_args()

    filters_output, dnr_rules = convert_filter_files(
    args.source
    )

    args.filters_output.write_text(
        json.dumps(
            filters_output,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    args.rules_output.write_text(
        json.dumps(
            dnr_rules,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    stats = filters_output["metadata"]["statistics"]

    print(f"Wrote cosmetic rules: {args.filters_output}")
    print(f"Wrote network rules:  {args.rules_output}")
    print(f"Chrome DNR rules:     {len(dnr_rules)}")
    print(
        "Cosmetic rules:      "
        f"{len(filters_output['cosmeticRules'])}"
    )
    print(
        "Unsupported skipped: "
        f"{stats['unsupportedRulesSkipped']}"
    )
    print(
        "Duplicates removed:  "
        f"{stats['duplicatesRemoved']}"
    )
    print(
        "Source files:         "
        f"{stats['sourceFilesProcessed']}"
    )


if __name__ == "__main__":
    main()