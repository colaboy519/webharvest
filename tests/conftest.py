import pytest


@pytest.fixture
def sample_html():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Test Page</title>
        <meta name="description" content="A test page for WebHarvest">
        <meta property="og:title" content="OG Test Title">
        <meta property="og:image" content="https://example.com/image.jpg">
    </head>
    <body>
        <nav><a href="/home">Home</a></nav>
        <main>
            <h1>Hello WebHarvest</h1>
            <p>This is the main content of the page.</p>
            <a href="https://example.com/page1">Link 1</a>
            <a href="/page2">Link 2</a>
        </main>
        <footer>Footer content</footer>
        <script>console.log('strip me')</script>
    </body>
    </html>
    """
