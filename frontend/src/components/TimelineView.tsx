import React, { useMemo } from 'react';

interface TimelineEvent {
    time: string;
    type: string;
    label: string;
    severity: 'info' | 'low' | 'medium' | 'high' | 'critical';
    details?: any;
}

interface TimelineViewProps {
    events: TimelineEvent[];
    onRangeChange: (start: number, end: number) => void;
    className?: string;
}

const TimelineView: React.FC<TimelineViewProps> = ({ events, onRangeChange, className }) => {
    // 1. Sort and Parse Dates
    const sortedEvents = useMemo(() => {
        return [...events].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
    }, [events]);

    if (sortedEvents.length === 0) return <div className="p-4 text-slate-400 text-xs">No timeline data available.</div>;

    const startTime = new Date(sortedEvents[0].time).getTime();
    const endTime = new Date(sortedEvents[sortedEvents.length - 1].time).getTime();
    const duration = endTime - startTime || 1; // Avoid div by zero

    // 2. Bucketize for Density Plot (e.g., 50 buckets)
    const buckets = useMemo(() => {
        const bucketCount = 50;
        const bucketSize = duration / bucketCount;
        const counts = new Array(bucketCount).fill(0);

        sortedEvents.forEach(e => {
            const t = new Date(e.time).getTime();
            const idx = Math.min(Math.floor((t - startTime) / bucketSize), bucketCount - 1);
            counts[idx]++;
        });
        const maxCount = Math.max(...counts, 1);
        return counts.map(c => c / maxCount); // Normalize 0-1
    }, [sortedEvents, startTime, duration]);


    // 3. Render
    return (
        <div className={`flex flex-col h-full w-full ${className}`}>
            <div className="flex justify-between text-xs text-slate-500 mb-1 px-1">
                <span>{new Date(startTime).toLocaleString()}</span>
                <span>{new Date(endTime).toLocaleString()}</span>
            </div>

            <div className="relative h-16 bg-slate-100 rounded border border-slate-200 w-full">
                {/* Density Plot (SVG) */}
                <div className="absolute inset-0 p-1 flex items-end justify-between gap-[1px]">
                    {buckets.map((height, i) => (
                        <div
                            key={i}
                            style={{ height: `${height * 100}%` }}
                            className="flex-1 bg-slate-300 hover:bg-slate-400 transition-colors"
                        ></div>
                    ))}
                </div>

                {/* Critical Event Markers */}
                <div className="absolute inset-0 pointer-events-none">
                    {sortedEvents.filter(e => e.severity === 'critical' || e.severity === 'high').map((e, i) => {
                        const pos = (new Date(e.time).getTime() - startTime) / duration;
                        return (
                            <div
                                key={i}
                                className="absolute bottom-0 w-[2px] h-full bg-red-500 opacity-60"
                                style={{ left: `${pos * 100}%` }}
                                title={`${e.type}: ${e.label}`}
                            ></div>
                        );
                    })}
                </div>

                {/* TODO: Add Range Slider Interaction overlay here if needed */}
            </div>

            {/* Simple Range Inputs for "Playback" (MVP) */}
            <div className="mt-2 flex items-center gap-2">
                <input
                    type="range"
                    min={startTime}
                    max={endTime}
                    defaultValue={endTime}
                    className="w-full h-1 bg-slate-200 rounded-lg appearance-none cursor-pointer range-sm"
                    onChange={(e) => onRangeChange(startTime, parseInt(e.target.value))}
                />
                <span className="text-xs font-bold text-slate-600">Playback</span>
            </div>
        </div>
    );
};

export default TimelineView;
