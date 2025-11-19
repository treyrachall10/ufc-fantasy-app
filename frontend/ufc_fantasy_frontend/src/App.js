import './App.css';

function App() {

  const testAPI = async () => {
    try {
      const response = await fetch("http://localhost:8000/fighters/2868/");
      const data = await response.json();
      console.log("API Response:", data);
      alert("Check console for results!");
    } catch (error) {
      console.error(error);
      alert("API request failed. Check console.");
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>UFC Fantasy Test</h1>
        <button onClick={testAPI}>Test Fighter API</button>
      </header>
    </div>
  );
}

export default App;
