from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in geolife_agritech/__init__.py
from geolife_agritech import __version__ as version

setup(
	name="geolife_agritech",
	version=version,
	description="Application for Geolife Agritech",
	author="Erevive Technologies",
	author_email="laxmantandon@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
