from setuptools import setup, find_packages

setup(
    name='zono',
    version='0.2.0',
    description='A multipurpose python package',
    long_description="""# Zono: A Versatile Python Framework for Cryptography, Networking, CLI, and More

Zono is a comprehensive Python framework that provides a wide range of functionalities, making it easier to develop secure applications, build networked services, create command-line interfaces, handle settings and configurations, work with schemas, manage logging, orchestrate events, manage queues, utilize storage classes, resolve MAC vendor information, and play songs from YouTube playlists. Zono is designed to streamline development and empower developers to build powerful applications quickly and efficiently.

## Features

- **Cryptography**: Zono integrates the `cryptography` module to offer robust encryption and decryption mechanisms, ensuring secure communication and data protection.

- **Networking**: Utilize Zono's socket server and client modules to build networked applications with ease. Whether you're creating chat applications, real-time systems, or other networked services, Zono's networking tools provide a solid foundation.

- **Command-Line Interface (CLI)**: Zono includes a feature-rich CLI module, enabling you to create user-friendly command-line interfaces for your applications. Customize commands, options, and arguments to meet your application's needs.

- **Settings and Configurations**: Simplify the management of application settings and configurations using Zono's settings module. Load, modify, and save settings effortlessly.

- **Schema Handling**: Zono offers schema tools to validate and manage structured data. Ensure data integrity and adherence to predefined formats using schema definitions.

- **Logging and Events**: Take control of logging with Zono's logging module. Additionally, orchestrate events within your application using the event management capabilities.

- **Queue Management**: Utilize Zono's queue classes to manage asynchronous tasks, job processing, and event-driven workflows.

- **Storage Classes**: Simplify data storage with Zono's storage classes, which provide easy-to-use interfaces for working with various storage solutions.

- **MAC Vendor Information**: Resolve MAC vendor information using Zono's built-in MAC vendor lookup feature, enhancing network diagnostics.

- **Song Playback and YouTube Playlist Loading**: Enjoy audio playback features, including the ability to play songs from YouTube playlists. Zono offers integration with song playback and playlist loading.
""",
    long_description_content_type='text/markdown',
    url='https://github.com/KisAwesome/zono/',
    author='Kareem Fares',
    author_email='kareem.khaled.fares@gmail.com',
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
