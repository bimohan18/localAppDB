from setuptools import setup, find_packages

setup(
    name='localAppDB',
    version='0.1',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask',
        'Flask-SQLAlchemy',
        'oracledb'
    ],
    entry_points={
        'console_scripts': [
            'localAppDB=main:app.run'
        ]
    },
)