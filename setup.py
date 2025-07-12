from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="youtube-playlist-manager",
    version="1.0.0",
    author="YouTube Playlist Manager",
    author_email="your-email@example.com",
    description="A comprehensive Python tool for managing YouTube playlists with intelligent duplicate detection and automatic merging",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/youtube-playlist-manager",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "youtube-playlist-manager=main:main",
            "youtube-quota-checker=quota_checker:check_quota",
            "youtube-lightweight=lightweight_manager:main",
        ],
    },
    keywords="youtube playlist manager duplicate merge organize",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/youtube-playlist-manager/issues",
        "Source": "https://github.com/yourusername/youtube-playlist-manager",
        "Documentation": "https://github.com/yourusername/youtube-playlist-manager#readme",
    },
) 