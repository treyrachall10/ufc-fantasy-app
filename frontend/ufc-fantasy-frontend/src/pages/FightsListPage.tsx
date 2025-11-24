import ListPageLayout from "../components/ListPageLayout";
import ListHeader from "../components/ListHeader";
import FightsList from "../components/FightsList";

export default function FightsListPage() {
    return (
        <ListPageLayout>
            <ListHeader title="Fights" searchBarLabel="Search by fight"></ListHeader>
            <FightsList></FightsList>
        </ListPageLayout>
    )
}