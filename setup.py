import setuptools

setuptools.setup(
  name='bswitch',
  version='0.0.0',
  description='switch statement for python using bytecode mangling and binary search',
  classifiers=[],
  keywords=['switch','bytecode','decorator'],
  author='Abe Winter',
  author_email='abe-winter@users.noreply.github.com',
  url='https://github.com/abe-winter/bswitch',
  license='MIT',
  packages=setuptools.find_packages(exclude=('test','examples')),
)
