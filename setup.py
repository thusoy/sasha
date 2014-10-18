from setuptools import setup, find_packages

setup(
    name="sasha",
    version="0.1.0",
    packages=find_packages(),
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
    }
)
