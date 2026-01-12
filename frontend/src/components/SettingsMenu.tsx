import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
  IconButton
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import TaxFundingPolicy from './TaxFundingPolicy';
import TaxTablesEditor from './TaxTablesEditor';
import TaxTableIndexingPolicy from './TaxTableIndexingPolicy';

type SettingsView = 'menu' | 'tax_funding' | 'tax_tables' | 'indexing_policy';

interface SettingsMenuProps {
  open: boolean;
  onClose: () => void;
  scenarioId: number;
}

const SettingsMenu: React.FC<SettingsMenuProps> = ({ open, onClose, scenarioId }) => {
  const [currentView, setCurrentView] = useState<SettingsView>('menu');

  const handleBack = () => {
    setCurrentView('menu');
  };

  const handleClose = () => {
    setCurrentView('menu');
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>
            {currentView === 'menu' && 'Settings'}
            {currentView === 'tax_funding' && 'Tax Funding Policy'}
            {currentView === 'tax_tables' && 'Tax Tables'}
            {currentView === 'indexing_policy' && 'Tax Table Indexing Policy'}
          </span>
          <IconButton onClick={handleClose} size="small">
            <CloseIcon />
          </IconButton>
        </div>
      </DialogTitle>
      <DialogContent>
        {currentView === 'menu' && (
          <List>
            <ListItem disablePadding>
              <ListItemButton onClick={() => setCurrentView('tax_funding')}>
                <ListItemText 
                  primary="Tax Funding Policy"
                  secondary="Configure how taxes are paid from available assets"
                />
              </ListItemButton>
            </ListItem>
            <Divider />
            <ListItem disablePadding>
              <ListItemButton onClick={() => setCurrentView('tax_tables')}>
                <ListItemText 
                  primary="Tax Tables"
                  secondary="Edit federal and state tax brackets and standard deductions"
                />
              </ListItemButton>
            </ListItem>
            <Divider />
            <ListItem disablePadding>
              <ListItemButton onClick={() => setCurrentView('indexing_policy')}>
                <ListItemText 
                  primary="Tax Table Indexing Policy"
                  secondary="Configure how tax thresholds adjust over time"
                />
              </ListItemButton>
            </ListItem>
          </List>
        )}
        
        {currentView === 'tax_funding' && (
          <TaxFundingPolicy scenarioId={scenarioId} onBack={handleBack} onClose={handleClose} />
        )}
        
        {currentView === 'tax_tables' && (
          <TaxTablesEditor scenarioId={scenarioId} onBack={handleBack} onClose={handleClose} />
        )}
        
        {currentView === 'indexing_policy' && (
          <TaxTableIndexingPolicy scenarioId={scenarioId} onBack={handleBack} onClose={handleClose} />
        )}
      </DialogContent>
    </Dialog>
  );
};

export default SettingsMenu;

