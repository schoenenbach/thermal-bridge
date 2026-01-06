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

import json
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from backend.core.scenario_schema import Scenario

def generate_schema(output_path="scenario_schema.json"):
    """Generates the JSON schema for the Scenario model."""
    schema = Scenario.model_json_schema()
    
    with open(output_path, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"✅ Schema generated at: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    generate_schema()
