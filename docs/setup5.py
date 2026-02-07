---

## 📝 CREATE setup.py ENTRY POINT
#python -m step5_coverage --config .tbeval.yaml #command to run
Add to `setup.py`:

```python
from setuptools import setup, find_packages

setup(
    name="step5_coverage",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=5.0",
    ],
    entry_points={
        'console_scripts': [
            'tbeval-coverage=step5_coverage.__main__:main',
        ],
    },
    python_requires='>=3.7',
)
