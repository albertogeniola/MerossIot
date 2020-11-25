import asyncio

from livereload import Server, shell

# The first line is needed for Windows and Python 3.8
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
server = Server()
server.watch('*.rst', shell('make html', cwd='docs'))
server.serve(root='_build/html')
