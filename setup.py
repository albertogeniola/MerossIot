from os import path

from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

with open(path.join(here, '.version'), encoding='utf-8') as f:
    TARGET_VERSION = f.read()

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='meross_iot',
    version=TARGET_VERSION,
    packages=find_packages(exclude=('tests',)),
    url='https://github.com/albertogeniola/MerossIot',
    license='MIT',
    author='Alberto Geniola',
    author_email='albertogeniola@gmail.com',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent'
    ],
    description='A simple library to deal with Meross devices. At the moment MSS110, MSS210, MSS310, MSS310H '
                'smart plugs and the MSS425E power strip. Other meross device might work out of the box with limited '
                'functionality. Give it a try and, in case of problems, let the developer know by opening an issue '
                'on Github.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='meross smartplug smartbulb iot mqtt domotic switch MSL120 MSS110 MSS210 MSS310 MSS310h '
             'MSS425e MSS530H MSG100 MSH300 MS100 MSS710 MSXH0',
    data_files=[('.', ['.version'])],
    project_urls={
        'Documentation': 'https://github.com/albertogeniola/MerossIot',
        'Funding': 'https://donate.pypi.org',
        'Source': 'https://github.com/albertogeniola/MerossIot',
        'Tracker': 'https://github.com/albertogeniola/MerossIot/issues',
    },
    install_requires=[
        'paho-mqtt>=1.3.1',
        'requests>=2.19.1',
        'retrying>=1.3.3',
        'aiohttp[speedups]==3.6.2'
    ],
    python_requires='>=3.7',
    test_suite='tests',
    entry_points={
        'console_scripts': ['meross_sniffer=utilities.meross_sniffer:main', 'meross_api_cli=meross_iot.http_api:main']
    }
)
