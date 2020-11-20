# version is a human-readable version number.

# version_info is a four-tuple for programmatic comparison. The first
# three numbers are the components of the version number. The fourth
# is zero for an official release, positive for a development branch,
# or negative for a release candidate or beta (after the base version
# number has been incremented)
__version__ = '0.1.0'
version_info = (0, 1, 0, 0)

PUBLICATION_TYPES = {
    "journal": "Journal Article",
    "proceeding": "Conference Proceeding",
    "thesis": "Thesis",
    "other": "Other",
}

PROJECTS = {
    'icecube': 'IceCube',
    'ara': 'ARA',
    'bigdata': 'BigData',
    'cta': 'CTA',
    'dm-ice': 'DM-Ice',
    'hawc': 'HAWC',
}

SITES = {
    'icecube': 'IceCube',
    'ara': 'ARA',
    'wipac': 'WIPAC',
}
