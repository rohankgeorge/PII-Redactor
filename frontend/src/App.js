import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Home from "@/pages/Home";

function App() {
  return (
    <div className="dark min-h-screen bg-background text-foreground">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </BrowserRouter>
      <Toaster theme="dark" richColors position="top-right" />
    </div>
  );
}

export default App;
