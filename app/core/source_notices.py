"""Publisher notices for the reviewed, unchanged excerpt delivery mode."""
NHS_NOTICE = (
    "Information from the NHS website is licensed under the Open Government Licence v3.0 "
    "(https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). "
    "Unchanged excerpts carry their copy date and original source link. "
    "No NHS endorsement is implied. A paid service must not levy a specific charge for NHS content."
)
CDC_NOTICE = (
    "Source: Centers for Disease Control and Prevention (CDC). "
    "Use of this material and its links does not imply endorsement by CDC, ATSDR, HHS or the United States Government "
    "of CancerInfo, its users, companies, products or services. "
    "The original material is available on the CDC website for no charge. "
    "Preserve substantive content, source attribution and this notice; do not use agency logos or frame CDC pages."
)
WHO_LICENSE_ID = "CC BY-NC-SA 3.0 IGO"
WHO_LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/3.0/igo/"
WHO_NOTICE = (
    "Content from the World Health Organization (WHO) is licensed under the Creative Commons "
    f"Attribution-NonCommercial-ShareAlike 3.0 IGO license ({WHO_LICENSE_ID}; {WHO_LICENSE_URL}). "
    "WHO content is served only for approved noncommercial use, never on the commercial access path, "
    "and always with its source attribution. No WHO endorsement is implied."
)
SOURCE_NOTICE = NHS_NOTICE + " " + CDC_NOTICE + " " + WHO_NOTICE
