from setuptools import setup, find_packages

setup(
    name='your-package-name',
    version='0.1.0',
    description='A multipurpose python package',
    long_description='Detailed description of your package',
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/your-package',
    author='Kareem Fares',
    author_email='your@email.com',
    license='MIT',
    
    packages=find_packages(),
    install_requires=[
        'base58==2.1.1',
        'colorama==0.4.6',
        'cryptography==41.0.1',
        'mutagen==1.46.0',
        'pafy==0.5.5',
        'python-vlc==3.0.18122',
        'PyYAML==6.0.1',
        'requests==2.31.0',
        'tqdm==4.65.0',
        'yt-dlp==2023.7.6',
    ],
    
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
