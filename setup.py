import distutils
import io
import pathlib

from setuptools import setup, find_packages
from distutils.cmd import Command
from distutils.command.build import build


if __name__ == '__main__':
    setup(
        name='psi-j-testing-service',
        version='0.1.0',

        description='''Aggregation server for PSI/J testing and test reports.''',

        author='The ExaWorks Team',
        author_email='hategan@mcs.anl.gov',

        url='https://github.com/exaworks/psi-j-testing-service',

        classifiers=[
            'Programming Language :: Python :: 3',
            'License :: OSI Approved :: MIT License',
        ],


        packages=find_packages(where='src'),
        package_dir={'': 'src'},

        package_data={
            '': ['README.md', 'LICENSE', 'web']
        },


        scripts=[],

        entry_points={
            'console_scripts': [
                'psi-j-testing-service = psij.testing.service:main'
            ]
        },

        install_requires=pathlib.Path('requirements.txt').read_text().split('\n'),
        python_requires='>=3.6'
    )
