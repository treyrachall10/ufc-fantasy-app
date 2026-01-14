import HighchartsReact from 'highcharts-react-official';
import Highcharts from 'highcharts';

export default function LeagueStandingsBarChart() {

    const data = [
    { category: "Iron Fist FC", points: 184 },
    { category: "Bloodline MMA", points: 162 },
    { category: "Apex Predators", points: 201 },
    { category: "Submission Syndicate", points: 139 },
    { category: "Knockout Kings", points: 225 },
    { category: "Ground Zero Gym", points: 121 },
    { category: "Warpath Fight Team", points: 173 },
    ];

        const options = {
            chart: {
                type: 'bar',
                backgroundColor: 'hsla(150, 8%, 5%, 1)',
                spacing: [16, 16, 16, 16],
                height: 700,
                marginLeft: 275,
            },
            title: {
                text: 'League Standings',
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
                    enabled: false,
                    reserveSpace: true,
                    style: {
                        color: 'white',
                        fontWeight: '300',
                        letterSpacing: '0.03em',
                        },
                },
                title: {
                    text: 'Teams',
                    enabled: false,
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
                    name: 'Team Name',
                    data: data.map(d => d.points),
                    color: 'hsla(0, 91%, 43%, 0.3)',
                    borderWidth: 1,
                    borderColor: 'hsla(0, 91%, 43%, 1)',
                    tooltip: {
                        followPointer: true,
                    }
                },
                ],
            plotOptions: {
                bar: {
                    borderRadius: 1,
                    borderWidth: 0,
                    pointWidth: 26,
                    pointPadding: 1,
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