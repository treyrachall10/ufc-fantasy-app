import type { Fighter } from '../../types/types';
import HighchartsReact from 'highcharts-react-official';
import Highcharts from 'highcharts';

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

           const options = {
        chart: {
            type: 'bar',
            backgroundColor: 'hsla(150, 8%, 5%, 1)',
            spacing: [16, 16, 16, 16],
        },
        title: {
            text: 'Win Loss',
            align: 'Left',
            style: {
                fontSize: '1rem',
                lineHeight: '1.3rem',
                letterSpacing: '0.01em',
                fontWeight: 500,
            }
        },
        legend: {
            floating: true,
            align: 'right',
            verticalAlign: 'bottom',
            layout: 'vertical',
            borderWidth: 1,
            borderRadius: 2,
            x: -10,
            y: -10,
            symbolRadius: 2,
            itemStyle: {
                color: "hsla(0, 0%, 100%, 0.5)",
            }
        },
        xAxis: {
            categories: data.map(d => d.category),
            gridLineWidth: 0,
            lineWidth: 0,
            offset: -5,
            labels: {
                style: {
                    color: 'white',
                    fontWeight: '300',
                    letterSpacing: '0.03em'
                    },
            },
            title: {
                text: 'Methods'
            }
        },
        yAxis: {
            min: 0,
            gridLineWidth: 0,
            lineWidth: 0,
            title: false,
            labels: {
                enabled: false,
            },

        },
        series: [
            {
                name: 'Wins',
                data: data.map(d => d.W),
                color: 'hsla(0, 91%, 43%, 0.75)',
                borderWidth: 1,
                borderColor: 'hsla(0, 91%, 43%, 1)',
            },
            {
                name: 'Losses',
                data: data.map(d => d.L),
                color: 'hsla(0, 91%, 43%, 0.3)',
                borderWidth: 1,
                borderColor: 'hsla(0, 91%, 43%, 1)',
            },
            ],
        plotOptions: {
            bar: {
                borderRadius: 1,
                borderWidth: 0,
                pointPadding: 0.15,
                dataLabels: {
                    enabled: true,
                    style: {
                        fontWeight: '500',
                        textOutline: 'none',
                        textShadow: 'none',
                    }
                }
            }
        },
        tooltip: {
            pointFormat: '{point.y} {series.name} by {point.category}',
            backgroundColor: 'hsla(135, 8%, 10%, 1)',
            style: {
                color: 'white',
            }
        },
        credits: {
            enabled: false,
        }
        } 
    
    return (
        <HighchartsReact
        highcharts={Highcharts}
        options={options}/>
    )
}