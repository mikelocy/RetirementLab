import React from 'react';
import { Routes, Route } from 'react-router-dom';
import ScenarioList from './components/ScenarioList';
import ScenarioDetail from './components/ScenarioDetail';

const AppRouter: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<ScenarioList />} />
      <Route path="/scenarios/:id" element={<ScenarioDetail />} />
    </Routes>
  );
};

export default AppRouter;

