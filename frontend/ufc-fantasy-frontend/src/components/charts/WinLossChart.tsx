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
        { category: "Unanimous Decision", W: record?.wins.unanimous_decision_wins, L: record?.losses.unanimous_decision_losses },
        { category: "Majority Decision", W: record?.wins.majority_decision_wins, L: record?.losses.majority_decision_losses },
        { category: "Doctor Stoppage", W: record?.wins.tko_doctor_stoppage_wins, L: record?.losses.tko_doctor_stoppage_losses },
        { category: "DQ", W: record?.wins.dq_wins, L: record?.losses.dq_losses },
    ];
    return (
        <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
                <Bar dataKey="W" fill="green" barSize={"2.5%"}/>
                <Bar dataKey="L" fill="red" barSize={"2.5%"}/>
                <CartesianGrid stroke="#ccc" />
                <XAxis dataKey="category" tick={{fontSize: 10}} interval={0} angle={-30} textAnchor='end'/>
                <YAxis />
                <Tooltip/>
            </BarChart>
        </ResponsiveContainer>
    )
}