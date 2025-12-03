import Box from "@mui/material/Box";
import DivergingProgressBar from "./DivergingProgressBar";
import { Typography } from "@mui/material";

interface HeadToHeadStatCardProps {
  title: string;
  leftValue: number;
  rightValue: number;
  leftColor?: string;
  rightColor?: string;
}

export default function HeadToHeadStatCard({
  title,
  leftValue,
  rightValue,
  leftColor = 'red',
  rightColor = 'black'
}: HeadToHeadStatCardProps) {

  return (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      gap: 1,
      p: 2,
      border: 1
      }}>
        <Typography variant="subtitle2">{title}</Typography>
        <Box sx={{
          display: 'flex',
          width: '50%',
          gap: 1
        }}>
          <Typography variant="body1">{leftValue}</Typography>
          <DivergingProgressBar leftValue={leftValue} rightValue={rightValue} sx={{ width: '100%' }}/>
          <Typography variant="body1">{rightValue}</Typography>
        </Box>
      </Box>
        
  );
}
