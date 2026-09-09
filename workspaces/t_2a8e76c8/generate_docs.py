"""Generate the documentation site."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from canvasui import create_default_site

site = create_default_site()
site.generate("docs_site.html")
print("Docs site generated successfully")
print("File size:", len(open("docs_site.html").read()), "bytes")
