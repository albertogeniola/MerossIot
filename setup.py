from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='meross-iot',
    version='0.1.1.1',
    packages=['.', 'supported_devices'],
    url='https://github.com/albertogeniola/MerossIot',
    license='MIT',
    author='Alberto Geniola',
    author_email='albertogeniola@gmail.com',
    classifiers=[
              'Development Status :: 4 - Beta',
              'Intended Audience :: Developers',
              'Programming Language :: Python :: 3'
          ],
    description='A simple library to deal with Meross MSS310 smart plug',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='meross smartplug iot mqtt domotic switch',
    project_urls={
    'Documentation': 'https://github.com/albertogeniola/MerossIot',
    'Funding': 'https://donate.pypi.org',
    'Source': 'https://github.com/albertogeniola/MerossIot',
    'Tracker': 'https://github.com/albertogeniola/MerossIot/issues',
    },
    python_requires='>=3'
)
