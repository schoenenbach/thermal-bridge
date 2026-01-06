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

import React, { useRef } from 'react';
import { Stage, Layer } from 'react-konva';
import Konva from 'konva';

interface StageCanvasProps {
    width: number;
    height: number;
    scale: number;
    onWheel: (e: any) => void;
    children: React.ReactNode;
}

const StageCanvas: React.FC<StageCanvasProps> = ({ width, height, scale, onWheel, children }) => {
    const stageRef = useRef<Konva.Stage>(null);

    return (
        <Stage
            width={width}
            height={height}
            scaleX={scale}
            scaleY={scale}
            onWheel={onWheel}
            draggable
            ref={stageRef}
            style={{ border: '1px solid #ccc', backgroundColor: '#f0f0f0' }}
        >
            <Layer>
                {children}
            </Layer>
        </Stage>
    );
};

export default StageCanvas;
