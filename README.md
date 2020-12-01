# publication-web-db
Publication Website / Database


## Organization

### Main (route: /)

Displays publications, and can be filtered.

Filters:
* Project
* Start Date
* End Date
* Type
  * Conference Proceeding
  * Journal Article
  * Thesis
  * Other
* Title
* Authors

Can also disable displaying projects, to lock to a single one.

An additional hidden filter is the `site`, to display a single site view.

### JSON API (route: /api/*)

A json view, designed for external site integration
with the `/static/external.js` library. See `pubs/static/external.html`
for an example.

### Manage (route: /manage)

Manage existing publications, if authorized to do so.

This route is responsible for creating, editing, and deleting publications.

## Publication Details

Properties of a publication:

* Title
* Authors
* Type
* Journal Citation
* Date
* Download link(s)
* Project(s)
* Site(s)

# Server Setup

## Nginx

CORS will need to be enabled for external rendering:
[https://enable-cors.org/server_nginx.html](https://enable-cors.org/server_nginx.html)

Otherwise, it uses a standard reverse-proxy setup to the python process.
TLS should be handled in Nginx, and `/static` may be served directly from
the `pubs/static` directory as an optimization.

