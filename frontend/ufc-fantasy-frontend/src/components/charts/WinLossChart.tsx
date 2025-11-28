import { BarChart, Legend, XAxis, YAxis, CartesianGrid, Tooltip, Bar, ResponsiveContainer} from 'recharts';

export default function WinLossChart() {
    const data = [
        { category: "KO/TKO", W: 10, L: 2 },
        { category: "Submission", W: 2, L: 1 },
        { category: "Decision", W: 5, L: 1 },
    ];
    return (
        <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
                <Bar dataKey="W" fill="green" barSize={"5%"}/>
                <Bar dataKey="L" fill="red" barSize={"5%"}/>
                <CartesianGrid stroke="#ccc" />
                <XAxis dataKey="category"/>
                <YAxis />
                <Legend/>
                <Tooltip/>
            </BarChart>
        </ResponsiveContainer>
    )
}