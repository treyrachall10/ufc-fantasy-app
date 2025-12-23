import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface FantasyTrendPoint {
    bout: string,
    points: number,
    date: string,
}

interface FantasyTrendLineChartProps {
    data: FantasyTrendPoint[]
}

export default function FantasyTrendLineChart({data}: FantasyTrendLineChartProps) {

    return (
        <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
                <Line type="monotone" dataKey="points" stroke="green"/>
                <CartesianGrid stroke="#ccc" />
                <XAxis dataKey="date"/>
                <YAxis />
                <Legend/>
                <Tooltip/>
            </LineChart>
        </ResponsiveContainer>
    )
}