import { BarChart, Legend, XAxis, YAxis, CartesianGrid, Tooltip, Bar, ResponsiveContainer} from 'recharts';

interface WinLossChartProps {
    koTko: {
        W: number;
        L: number;
    };
    submission: {
        W: number;
        L: number;
    };
    doctorStop: {
        W: number;
        L: number;
    };
    unanimousDecision: {
        W: number;
        L: number;
    };
    splitDecision: {
        W: number;
        L: number;
    };
    majorityDecision: {
        W: number;
        L: number;
    };
}

export default function WinLossChart({
   koTko,
   submission,
   doctorStop,
   unanimousDecision,
   splitDecision,
   majorityDecision,
}: WinLossChartProps) {
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