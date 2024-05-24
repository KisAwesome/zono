from .module_helper import ServerModule, middleware
import math
import os
import re


class FileHost(ServerModule):
    def __init__(
        self, public_dir, request_path="file", check_func=None, buffer_size=8192
    ):
        self.public_dir = public_dir
        self.request_path = request_path
        self.check_func = check_func
        self.buffer_size = buffer_size

    def parse_url(self, url):
        pattern = re.compile(r"^(.*?)(?:\?(\d+))?$")
        match = pattern.match(url)

        if match:
            return match.group(1), match.group(2)
        return None, None

    def get_file_chunk(self, file_path, buffer_size, chunk_index):
        with open(file_path, "rb") as file:
            file_size = os.path.getsize(file_path)

            start_byte = chunk_index * buffer_size
            end_byte = min((chunk_index + 1) * buffer_size, file_size)

            if start_byte >= file_size:
                return None

            file.seek(start_byte)
            data = file.read(end_byte - start_byte)

        return data

    def calculate_number_of_chunks(self, file_path, buffer_size):
        file_size = os.path.getsize(file_path)
        return math.ceil(file_size / buffer_size)

    @middleware
    def check_request(self, ctx):
        path = ctx.pkt.get("path", None)
        if path is None or not isinstance(path, str):
            return ctx.next()

        if path.startswith("/"):
            path = path[1:]

        spath = path.split("/")

        if spath[0] == self.request_path:
            spath.pop(0)
            file = os.path.join(self.public_dir, "/".join(spath))
            file, index = self.parse_url(file)
            if file is None:
                return ctx.send(
                    dict(
                        success=False, error=True, code=400, info="Incomplete file path"
                    )
                )
            if os.path.isfile(file) is False:
                return ctx.send(
                        dict(success=False, error=True, code=404, info="File not found")
                    )

            
            if index is None:
                return ctx.send(
                    dict(
                        success=True,
                        error=False,
                        code=200,
                        info="File exists",
                        chunks=self.calculate_number_of_chunks(
                            file, self.buffer_size
                        ),
                        size=os.stat(file).st_size,
                        buffer=self.buffer_size,
                        name=os.path.basename(file),
                    )
                )
                 

            if index.isdigit() is False:
                return ctx.send(
                    dict(success=False, error=True, code=400, info="Malformed path")
                )
            index = abs(int(index))
            ctx.app.send_raw(
                dict(
                    success=True,
                    error=False,
                    code=200,
                    info="",
                    chunk=index,
                    data=self.get_file_chunk(file, self.buffer_size, index),
                ),
                ctx.conn,
                ctx.app.buffer
            )

        else:
            ctx.next()
