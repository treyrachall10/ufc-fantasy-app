import HighchartsReact from 'highcharts-react-official';
import Highcharts from 'highcharts';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { wrap } from 'module';

interface FantasyTrendPoint {
    bout: string,
    points: number,
    date: string,
}

interface FantasyTrendLineChartProps {
    data: FantasyTrendPoint[]
}

export default function FantasyTrendLineChart({data}: FantasyTrendLineChartProps) {
    const options = {
        chart: {
            type: 'area',
            backgroundColor: 'hsla(150, 8%, 5%, 1)',
            spacing: [16, 16, 16, 16],
        },
        title: {
            text: 'Fantasy Trend',
            align: 'left',
            style: {
                fontSize: '1rem',
                lineHeight: '1.3rem',
                letterSpacing: '0.01em',
                fontWeight: 500,
            }
        },
        legend: {
            enabled: false,
        },
        xAxis: {
            categories: data.map(d => d.bout),
            labels: {
                color: "hsla(0, 0%, 100%, 0.5)",
                style: {
                    color: 'hsla(0, 0%, 100%, 0.3)',
                }
            },
            lineWidth: 0
        },
        yAxis: {
            title: {text: undefined},
            labels: {
                useHTML: true,
                formatter: function (
                this: Highcharts.AxisLabelsFormatterContextObject
                ) {
                if (this.isFirst) {
                    return '';
                }
                return `<div class="yax">${this.value}</div>`;
                },
                x: -20,
                y: 0,
                style: {
                    color: "hsla(0, 0%, 100%, 0.25)",
                }
            },
            gridLineColor: "hsla(0,0%,100%,0.1)",

            gridLineDashStyle: 'Dash',
            opposite: true,
        },
        tooltip: {
            pointFormat: '{series.name} scored {point.y} points during {point.category}',
            backgroundColor: 'hsla(135, 8%, 10%, 1)',
            style: {
                color: 'white',
            }
        },
        series: [{
            type: "area",
            name: 'fighter',
            data: data.map(d => d.points),
            color: "hsla(0, 91%, 43%, 1)",
            fillColor: "hsla(0, 91%, 43%, 0.05)",
            marker: {
                enabled: false, // Disable plot points
            },
            zones: [
                {dashStyle: 'Dot'} // Makes line dashed
            ]

        }],
        plotOptions: {
            series: {
                pointPlacement: 'on',
            },
        },
        credits: {
            enabled: false
        }
    }
    return (
        <HighchartsReact
        highcharts={Highcharts}
        options={options}/>
    )
}