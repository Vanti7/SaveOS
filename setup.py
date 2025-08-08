#!/usr/bin/env python3
"""
Configuration d'installation pour l'agent SaveOS
"""
from setuptools import setup, find_packages

setup(
    name="saveos-agent",
    version="1.1.0",
    description="Agent de sauvegarde pour le système SaveOS",
    author="SaveOS Team",
    author_email="contact@saveos.local",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.7",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "borgbackup>=1.2.6",
    ],
    entry_points={
        'console_scripts': [
            'saveos-agent=agent.cli:cli',
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Archiving :: Backup",
    ],
)