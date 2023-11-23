import os

from lona import View, Response, FileResponse


class FrontendView(View):
    FRONTEND_ROOT = os.path.join(
        os.path.dirname(__file__),
        '../frontend/static',
    )

    def get_not_found_error(self):
        return Response('404: Not Found', status=404)

    def get_file_response(self, path):
        return FileResponse(
            path,
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
            }
        )

    def handle_request(self, request):
        rel_path = request.match_info['path']

        if rel_path.startswith('/'):
            rel_path = rel_path[1:]

        abs_path = os.path.join(self.FRONTEND_ROOT, rel_path)

        if not os.path.exists(abs_path):
            return self.get_not_found_error()

        if os.path.isdir(abs_path):
            index_path = os.path.join(abs_path, 'index.html')

            if os.path.exists(index_path):
                return self.get_file_response(index_path)

            return self.get_not_found_error()

        return self.get_file_response(abs_path)
