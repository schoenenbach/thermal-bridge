/*
 * Copyright (C) 2026 Thomas
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import React from 'react';
import { Line, Group, Text } from 'react-konva';

interface PolygonShapeProps {
    id: string;
    points: number[];
    isSelected: boolean;
    onSelect: (id: string) => void;
}

const PolygonShape: React.FC<PolygonShapeProps> = ({ id, points, isSelected, onSelect }) => {
    return (
        <Group
            onClick={() => onSelect(id)}
        >
            <Line
                points={points}
                closed
                stroke={isSelected ? 'blue' : 'green'}
                strokeWidth={2}
                fill={isSelected ? 'rgba(0, 0, 255, 0.1)' : 'rgba(0, 255, 0, 0.1)'}
            />
            {points.length > 0 && (
                <Text
                    text="Poly"
                    x={points[0]}
                    y={points[1]}
                    fontSize={10}
                    opacity={0.5}
                />
            )}
        </Group>
    );
};

export default PolygonShape;
