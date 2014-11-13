# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md') as readme:
    _long_description = readme.read()

setup(
    name="sasha",
    version="0.1.1",
    packages=find_packages(),
    author='Martin Kirkholt Melhus, Tarjei Husøy',
    url='https://github.com/thusoy/sasha',
    description='Home automation over HTTP',
    long_description=_long_description,
    install_requires=[
        'flask',
        'requests',
    ],
    extras_require={
        'master': [
            'flask-sqlalchemy',
        ]
    },
    entry_points={
        'console_scripts': [
            'sasha = sasha:main',
            'sasha-master = sasha.master:main',
        ]
    },
    classifiers=[
        #'Development Status :: 1 - Planning',
        'Development Status :: 2 - Pre-Alpha',
        #'Development Status :: 3 - Alpha',
        #'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        #'Development Status :: 6 - Mature',
        #'Development Status :: 7 - Inactive',
        'Environment :: Console',
        'Environment :: MacOS X',
        'Environment :: Web Environment',
        'Environment :: Win32 (MS Windows)',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Adaptive Technologies',
        'Topic :: Home Automation',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ]
)
