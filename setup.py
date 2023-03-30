import distutils
import io
import os
import pathlib
from typing import List

from setuptools import setup, find_packages
from distutils.cmd import Command
from distutils.command.build import build


def get_files(root: str) -> List[str]:
    files = []
    for (path, dirs, fns) in os.walk(root):
        for fn in fns:
            files.append(os.path.join(path[len('src/psij/'):], fn))
    return files


if __name__ == '__main__':
    setup(
        name='psij-testing-service',
        version=pathlib.Path('RELEASE').read_text(),

        description='''Aggregation server for PSI/J testing and test reports.''',

        author='The ExaWorks Team',
        author_email='hategan@mcs.anl.gov',

        url='https://github.com/exaworks/psij-testing-service',

        classifiers=[
            'Programming Language :: Python :: 3',
            'License :: OSI Approved :: MIT License',
        ],


        packages=find_packages(where='src'),
        package_dir={'': 'src'},
        
        package_data={
            '': ['README.md', 'LICENSE', 'RELEASE'],
            'psij': get_files('src/psij/web')
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
