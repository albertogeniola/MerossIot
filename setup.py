from setuptools import setup

setup(
    name='meross-iot',
    version='0.1.0',
    packages=['.', 'supported_devices'],
    url='https://github.com/albertogeniola/MerossIot',
    license='MIT',
    author='Alberto Geniola',
    author_email='albertogeniola@gmail.com',
    description='A simple library to deal with Meross MSS310 smart plug',
    classifiers=[
              'Development Status :: 4 - Beta',
              'Intended Audience :: Developers',
              'Programming Language :: Python :: 3'
          ]
)
