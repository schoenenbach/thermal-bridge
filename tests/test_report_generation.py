# Copyright (C) 2026 Thomas
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import pytest
from backend.core.report_generator import generate_pdf_report

def test_generate_pdf_report(tmp_path):
    # Setup
    output_path = tmp_path / "test_report.pdf"
    image_path = "preview.png"
    
    # Create a dummy image if it doesn't exist
    if not os.path.exists(image_path):
        from PIL import Image
        img = Image.new('RGB', (100, 100), color = 'red')
        img.save(image_path)
    
    # Execute
    results = {"Psi": 0.1, "fRsi": 0.8}
    success, msg = generate_pdf_report("Test Project", "Tester", "Desc", results, image_path, str(output_path))
    
    # Verify
    assert success
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0
