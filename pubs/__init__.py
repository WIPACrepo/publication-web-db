# version is a human-readable version number.

# version_info is a four-tuple for programmatic comparison. The first
# three numbers are the components of the version number. The fourth
# is zero for an official release, positive for a development branch,
# or negative for a release candidate or beta (after the base version
# number has been incremented)
__version__ = '1.1.0'
version_info = (1, 1, 0, 0)

PUBLICATION_TYPES = {
    "journal": "Journal Article",
    "proceeding": "Conference Proceeding",
    "thesis": "Thesis",
    "other": "Other",
    "internal": "Internal Report",
}

PROJECTS = {
    'icecube': 'IceCube',
    'icecube-gen2': 'IceCube-Gen2',
    'ara': 'ARA',
    'bigdata': 'BigData',
    'cta': 'CTA',
    'dm-ice': 'DM-Ice',
    'hawc': 'HAWC',
    'other': 'Other',
}

SITES = {
    'icecube': 'IceCube',
    'icecube-gen2': 'IceCube-Gen2',
    'ara': 'ARA',
    'wipac': 'WIPAC',
}

FIELDS = [
    '_id',
    'title',
    'authors',
    'type',
    'citation',
    'date',
    'abstract',
    'downloads',
    'projects',
    'sites',
]