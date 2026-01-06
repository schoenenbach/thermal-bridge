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

import React, { useRef, useEffect } from 'react';
import { Rect, Group, Text, Transformer } from 'react-konva';

interface WallShapeProps {
    id: string;
    x: number;
    y: number;
    width: number;
    height: number;
    isSelected: boolean;
    onSelect: (id: string) => void;
    onChange: (id: string, newAttrs: { x: number; y: number; width: number; height: number }) => void;
}

const WallShape: React.FC<WallShapeProps> = ({ id, x, y, width, height, isSelected, onSelect, onChange }) => {
    const shapeRef = useRef<any>(null);
    const trRef = useRef<any>(null);

    useEffect(() => {
        if (isSelected && trRef.current && shapeRef.current) {
            trRef.current.nodes([shapeRef.current]);
            trRef.current.getLayer().batchDraw();
        }
    }, [isSelected]);

    const handleDragEnd = (e: any) => {
        onChange(id, {
            x: e.target.x(),
            y: e.target.y(),
            width, // Width/Height don't change on drag
            height,
        });
    };

    const handleTransformEnd = (e: any) => {
        // transformer is changing scale of the node
        // and rotation, but we only care about scale for now
        const node = shapeRef.current;
        const scaleX = node.scaleX();
        const scaleY = node.scaleY();

        // reset scale to 1 and update width/height
        node.scaleX(1);
        node.scaleY(1);

        onChange(id, {
            x: node.x(),
            y: node.y(),
            width: Math.max(5, node.width() * scaleX),
            height: Math.max(5, node.height() * scaleY),
        });
    };

    return (
        <React.Fragment>
            <Group
                x={x}
                y={y}
                draggable
                onClick={() => onSelect(id)}
                onDragEnd={handleDragEnd}
                ref={shapeRef}
                onTransformEnd={handleTransformEnd}
            >
                <Rect
                    width={width}
                    height={height}
                    fill={isSelected ? '#aaccff' : '#cccccc'}
                    stroke={isSelected ? 'blue' : 'black'}
                    strokeWidth={isSelected ? 2 : 1}
                />
                <Text
                    text="Wall"
                    fontSize={12}
                    padding={5}
                    x={0}
                    y={0}
                    opacity={0.5}
                />
            </Group>
            {isSelected && (
                <Transformer
                    ref={trRef}
                    boundBoxFunc={(oldBox, newBox) => {
                        // limit resize
                        if (newBox.width < 5 || newBox.height < 5) {
                            return oldBox;
                        }
                        return newBox;
                    }}
                />
            )}
        </React.Fragment>
    );
};

export default WallShape;
