#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" HTML Request handler
"""
import hashlib

from pathlib import Path
from typing import Optional

from .basehandler import BaseHandler


class HtmlHandler(BaseHandler):

    def initialize(self, path: str, filename: str):
        """
        """
        super().initialize()
        self._path = Path(path, filename)

    def get(self) -> None:
        """
        """
        if not self.request.path.endswith("/"):
            # XXX Redirect with realm only if
            # already present as argument
            realm = self.get_argument('REALM', default="")
            if realm:
                realm = f"?realm={realm}"
            self.redirect(self.request.path + f"/{realm}", permanent=True)
            return

        self.get_job_realm()
        
        self.set_headers()
        if self.should_return_304():
            self.set_status(304)
            return

        content = self.get_content()

        self.set_header("Content-Type", "text/html") 
        self.write(content)

    def set_headers(self):
        """ Set content and cached headers
        """
        self.set_etag_header()

    def should_return_304(self) -> bool:
        """Returns True if the headers indicate that we should return 304.
        """
        if self.request.headers.get("If-None-Match"):
            return self.check_etag_header()

        return False

    def compute_etag(self) -> Optional[str]:
        """ Compute etag
        """
        # Check modification time
        stat = self._path.stat()
        
        hasher = hashlib.sha1()
        hasher.update(str(stat.st_mtime).encode())
        if self._realm:
            hasher.update(self._realm.encode())
        return f"'{hasher.hexdigest()}'"

    def get_content(self) -> Optional[bytes]:
        """ Get the html content 
        """
        with self._path.open("rb") as file:
            content = file.read()

        content = content.replace(b'%META%', (self._realm or '').encode(), 1)
        return content

    def get_job_realm(self):
        # Get the job realm
        realm = self.request.headers.get('X-Job-Realm')
        if realm is None:
            # Fallback to query param
            realm = self.get_argument('REALM', default=None)
        self._realm = realm


