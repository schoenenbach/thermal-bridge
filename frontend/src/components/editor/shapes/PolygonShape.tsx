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
