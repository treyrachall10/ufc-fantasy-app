import ListPageLayout from "../components/layout/ListPageLayout";
import ListHeader from "../components/ListHeader";
import FightsList from "../components/lists/FightsList";

export default function FightsListPage() {
    return (
        <ListPageLayout>
            <ListHeader title="Fights" searchBarLabel="Search by fight"></ListHeader>
            <FightsList></FightsList>
        </ListPageLayout>
    )
}