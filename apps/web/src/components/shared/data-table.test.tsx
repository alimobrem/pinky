import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { DataTable, type Column } from "./data-table";

interface TestRow {
  id: string;
  name: string;
  count: number;
}

const testData: TestRow[] = [
  { id: "1", name: "Alpha", count: 10 },
  { id: "2", name: "Beta", count: 20 },
  { id: "3", name: "Gamma", count: 5 },
];

const columns: Column<TestRow>[] = [
  { id: "name", header: "Name", cell: (row) => row.name },
  { id: "count", header: "Count", cell: (row) => row.count },
];

const keyFn = (row: TestRow) => row.id;

describe("DataTable", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders column headers", () => {
    render(<DataTable data={testData} columns={columns} keyFn={keyFn} />);
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Count")).toBeInTheDocument();
  });

  it("renders rows from data", () => {
    render(<DataTable data={testData} columns={columns} keyFn={keyFn} />);
    expect(screen.getAllByText("Alpha").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Beta").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Gamma").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("10").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("20").length).toBeGreaterThanOrEqual(1);
  });

  it("shows empty state when data is empty", () => {
    render(
      <DataTable
        data={[]}
        columns={columns}
        keyFn={keyFn}
        emptyState={<div>Nothing here</div>}
      />,
    );
    expect(screen.getAllByText("Nothing here").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryAllByText("Name")).toHaveLength(0);
  });

  it("shows loading state when isLoadingMore is true", () => {
    render(
      <DataTable
        data={testData}
        columns={columns}
        keyFn={keyFn}
        hasMore
        isLoadingMore
        onLoadMore={vi.fn()}
      />,
    );
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows Load more button when hasMore is true", () => {
    const onLoadMore = vi.fn();
    render(
      <DataTable
        data={testData}
        columns={columns}
        keyFn={keyFn}
        hasMore
        onLoadMore={onLoadMore}
      />,
    );
    const btn = screen.getByText("Load more");
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(onLoadMore).toHaveBeenCalledOnce();
  });

  it("hides Load more button when hasMore is false", () => {
    render(
      <DataTable
        data={testData}
        columns={columns}
        keyFn={keyFn}
        hasMore={false}
      />,
    );
    expect(screen.queryAllByText("Load more")).toHaveLength(0);
  });

  it("shows total count when provided", () => {
    render(
      <DataTable
        data={testData}
        columns={columns}
        keyFn={keyFn}
        totalCount={100}
      />,
    );
    expect(screen.getByText("Showing 3 of 100")).toBeInTheDocument();
  });

  it("calls onRowClick when a row is clicked", () => {
    const onClick = vi.fn();
    render(
      <DataTable
        data={testData}
        columns={columns}
        keyFn={keyFn}
        onRowClick={onClick}
      />,
    );
    fireEvent.click(screen.getAllByText("Alpha")[0]);
    expect(onClick).toHaveBeenCalledWith(testData[0]);
  });
});
