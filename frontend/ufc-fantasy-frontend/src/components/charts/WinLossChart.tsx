import { BarChart, Legend, XAxis, YAxis, CartesianGrid, Tooltip, Bar, ResponsiveContainer} from 'recharts';
import type { Fighter } from '../../types/types';

interface WinLossChartProps {
    record: Fighter['record'],
}

export default function WinLossChart({
   record
}: WinLossChartProps) {
    const data = [
        { category: "KO/TKO", W: record?.wins.ko_tko_wins, L: record?.losses.ko_tko_losses },
        { category: "Submission", W: record?.wins.submission_wins, L: record?.losses.submission_losses },
        { category: "Split Decision", W: record?.wins.split_decision_wins, L: record?.losses.split_decision_losses },
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