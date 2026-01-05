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
