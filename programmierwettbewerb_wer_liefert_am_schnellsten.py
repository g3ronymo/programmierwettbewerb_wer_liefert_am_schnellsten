#!/usr/bin/env python3
"""
Einreichung fuer:
https://gnulinux.ch/programmierwettbewerb-wer-liefert-am-schnellsten

von: geronymo
"""
import json
import re
import logging
import argparse
from  urllib import request
from urllib.error import HTTPError, URLError
from abc import abstractmethod


# https://dateutil.readthedocs.io/en/stable/index.html
#from dateutil.parser import isoparse 


def _url_content(url) -> bytes:
    try:
        with request.urlopen(url) as response:
            content = response.read()
    except HTTPError:
        return None
    except URLError:
        logging.warning("invalid url: " + url)
        return None
    return content


class Package:
    """Base class for all Packages"""

    def __init__(self, repository: str, name: str, distro='', distro_release=''):
        self.repository = repository
        self.name = name
        self.distro = distro
        self.distro_release = distro_release
        self.version = ''
        self.last_updated = ''
        self.update()

    @abstractmethod
    def update(self):
        pass


class PackageArchLinux(Package):
    def __init__(self, repository: str, name: str):
        super().__init__(repository, name, distro="ArchLinux", distro_release="")

    def update(self):
        url = "https://archlinux.org/packages/"
        url += str(self.repository)
        url += "/x86_64/"
        url += str(self.name)
        url += "/json/"
        package_info = _url_content(url)
        if package_info is None:
            return
        package_info = json.loads(package_info) 
        self.version = package_info["pkgver"]
        self.last_updated = package_info["last_update"].strip()


class PackageDebian(Package):
    def __init__(self, repository: str, name: str):
        super().__init__(repository, name, distro="Debian")

    def update(self):
        #url = f'https://tracker.debian.org/pkg/{self.name}'
        url = f'https://packages.debian.org/source/{self.repository}/{self.name}'
        html = _url_content(url)
        if html is None:
            return

        # regular expression to find version in html
        vp = f'<h1>Source Package: {self.name} \((.*?)\)\n</h1>'
        vp = bytes(vp, 'utf-8')
        match = re.search(vp, html)
        if match:
            self.version = match.group(1).decode()
        #TODO: find out when this package was added to unstable


class PackageFedora(Package):

    def __init__(self, repository: str, name: str, distro_release="37", source_package=None):
        if source_package is not None:
            self.source_package = source_package
        else:
            self.source_package = name
        super().__init__(repository, name, distro="Fedora", distro_release=distro_release)

    def update(self):
        url = f'https://packages.fedoraproject.org/pkgs/{self.source_package}/{self.name}/'
        html = _url_content(url)
        if html is None:
            return

        # regular expression to find version in html
        vp = f'<a href="fedora-{self.distro_release}.html">(.*?)</a>'
        vp = bytes(vp, 'utf-8')
        match = re.search(vp, html)
        if match:
            self.version = match.group(1).decode()
        #TODO: find out when this package was added to unstable


class PackageFlatPackFlatHub(Package):
    def __init__(self, name: str):
        super().__init__('flathub', name, distro='flatpak')

    def update(self):
        url = f'https://beta.flathub.org/apps/details/{self.name}'
        html = _url_content(url)
        if html is None:
            return

        # regular expression to find version in html
        vp = rb'<h3 class="my-0">Changes in version (.*?)</h3>'
        match = re.search(vp, html)
        if match:
            self.version = match.group(1).decode()

        up = rb'<div class="text-sm" title="([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})">.*?</div>'
        match = re.search(up, html)
        if match:
            month = match.group(1).decode()
            day = match.group(2).decode()
            year = match.group(3).decode()
            self.last_updated = year + '-' + month + '-' + day

def _pprint(packages: list[Package]):
    hline = '-' * (15+15+15+15)
    print('{:<15}{:<15}{:<15}{:<15}'.format(
        'distro',
        'repository',
        'version',
        'last updated',
        )
    )
    for p in packages:
        print(hline)
        print('{:<15}{:<15}{:<15}{:<15}'.format(
            str(p.distro) + " " + str(p.distro_release),
            str(p.repository),
            str(p.version),
            str(p.last_updated),
            )
        )
    
def main():
    SOFTWARE = ['firefox', 'thunderbird', 'libreoffice', 'inkscape', 'mesa']
    parser = argparse.ArgumentParser(
        description='Get information about the package versions of software')
    parser.add_argument(
        '-p', '--packages',
        nargs='+',
        choices=SOFTWARE,
        metavar='SOFTWARE',
        help='Space separated list of software-packages that should be'
        + ' displayed.'
        + f' Supported parameters are: {SOFTWARE}',
     )
    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Select all packages',
     )
    parser.add_argument(
        '-s', '--search',
        nargs=1,
        help='Search for a software using'
        + ' the same package name for all distros.'
        + ' This ignores the fact that software can have different names'
        + ' in different distros/repositorys.'
        + ' Distros with no result my still have the package but under a'
        + ' different name.',
    )
    args = parser.parse_args()


    selected_packages = []
    if args.packages:
        selected_packages = args.packages
    if args.all:
        selected_packages = SOFTWARE
    if args.search:
        _pprint([
            PackageArchLinux("core", args.search[0]),
            PackageArchLinux("extra", args.search[0]),
            PackageArchLinux("community", args.search[0]),
            PackageArchLinux("multilib", args.search[0]),
            PackageArchLinux("testing", args.search[0]),
            PackageArchLinux("community-testing", args.search[0]),
            PackageDebian("unstable", args.search[0]),
            PackageDebian("testing",  args.search[0]),
            PackageDebian("stable", args.search[0]),
            PackageFedora("stable", args.search[0]),
            PackageFedora("stable", args.search[0], distro_release='36'),
            PackageFlatPackFlatHub(args.search[0]),
        ])

    if 'firefox' in selected_packages:
        print("\nFirefox:")
        _pprint([
            PackageArchLinux("extra", "firefox"),
            PackageDebian("unstable", "firefox"),
            PackageDebian("testing", "firefox"),
            PackageDebian("stable", "firefox"),
            PackageFedora("stable", "firefox"),
            PackageFlatPackFlatHub("org.mozilla.firefox"),
        ])

    if 'thunderbird' in selected_packages:
        print("\nThunderbird:")
        _pprint([
            PackageArchLinux("extra", "thunderbird"),
            PackageDebian("unstable", "thunderbird"),
            PackageDebian("testing", "thunderbird"),
            PackageDebian("stable", "thunderbird"),
            PackageFedora("stable", "thunderbird"),
            PackageFlatPackFlatHub("org.mozilla.Thunderbird"),
        ])

    if 'libreoffice' in selected_packages:
        print("\nLibreOffice:")
        _pprint([
            PackageArchLinux("extra", "libreoffice-fresh"),
            PackageArchLinux("extra", "libreoffice-still"),
            PackageDebian("unstable", "libreoffice"),
            PackageDebian("testing", "libreoffice"),
            PackageDebian("stable", "libreoffice"),
            PackageFedora("stable", "libreoffice"),
            PackageFlatPackFlatHub("org.libreoffice.LibreOffice"),
        ])

    if 'inkscape' in selected_packages:
        print("\nInkscape:")
        _pprint([
            PackageArchLinux("extra", "inkscape"),
            PackageDebian("unstable", "inkscape"),
            PackageDebian("testing", "inkscape"),
            PackageDebian("stable", "inkscape"),
            PackageFedora("stable", "inkscape"),
            PackageFlatPackFlatHub("org.inkscape.Inkscape"),
        ])

    if 'mesa' in selected_packages:
        print("\nMesa:")
        _pprint([
            PackageArchLinux("extra", "mesa"),
            PackageDebian("unstable", "mesa"),
            PackageDebian("testing", "mesa"),
            PackageDebian("stable", "mesa"),
            # seems like Fedora has no package called mesa, and splits mesa in a lot 
            # of different packages.
            PackageFedora("stable", "mesa-libGL", source_package='mesa'),
        ])

if __name__ == "__main__":
    main()
