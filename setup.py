from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="supply-roster-optimization",
    version="1.0.0",
    description="A Streamlit application for optimizing supply roster management using OR-Tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="HaLim Jun",
    author_email="hjun@unicef.org",
    url="https://github.com/UNICEF-Ventures/SupplyDivision_Roster_Management",
    project_urls={
        "Bug Reports": "https://github.com/UNICEF-Ventures/SupplyDivision_Roster_Management/issues",
        "Source": "https://github.com/UNICEF-Ventures/SupplyDivision_Roster_Management",
        "Demo": "https://huggingface.co/spaces/OOI-FrontierTech/supply-roster-optimization",
    },
    packages=find_packages(),
    keywords="optimization, scheduling, supply-chain, streamlit, or-tools, workforce-management",
    install_requires=[
        "absl-py>=2.3.1",
        "dotenv>=0.9.9", 
        "immutabledict>=4.2.1",
        "numpy>=2.2.0",
        "ortools>=9.14.0",
        "pandas>=2.3.0",
        "plotly>=5.24.0",
        "protobuf>=3.20,<6",
        "psycopg2-binary>=2.9.9",
        "python-dateutil>=2.9.0",
        "python-dotenv>=1.0.0",
        "pytz>=2025.2",
        "six>=1.17.0",
        "SQLAlchemy>=2.0.36",
        "streamlit>=1.39.0",
        "typing_extensions>=4.14.0",
        "tzdata>=2025.2",
    ],
    python_requires=">=3.10,<3.11",
)
