import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function FantasyTrendLineChart() {
    const data = [
        { fight: "Islam vs. JDM", points: 120 },
        { fight: "Gary vs. Belal", points: 150 },
        { fight: "Oliveira vs. Poirier", points: 160 },
    ];
    return (
        <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
                <Line type="monotone" dataKey="points" stroke="green"/>
                <CartesianGrid stroke="#ccc" />
                <XAxis dataKey="fight"/>
                <YAxis />
                <Legend/>
                <Tooltip/>
            </LineChart>
        </ResponsiveContainer>
    )
}