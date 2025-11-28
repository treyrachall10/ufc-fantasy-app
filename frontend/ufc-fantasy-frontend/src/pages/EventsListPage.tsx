import ListPageLayout from "../components/layout/ListPageLayout";
import ListHeader from "../components/ListHeader";
import EventsList from "../components/lists/EventsList"

export default function EventsListPage() {
    return (
        <ListPageLayout>
            <ListHeader title="Events" searchBarLabel="Search by event"></ListHeader>
            <EventsList></EventsList>
        </ListPageLayout>
    )
}