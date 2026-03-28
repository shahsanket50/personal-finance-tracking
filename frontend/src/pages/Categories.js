import { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { Plus, Trash, Pencil } from '@phosphor-icons/react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Categories = () => {
  const [categories, setCategories] = useState([]);
  const [open, setOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    category_type: 'expense',
    color: '#5C745A'
  });

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const res = await axios.get(`${API}/categories`);
      setCategories(res.data);
    } catch (err) {
      toast.error('Failed to load categories');
      console.error(err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingCategory) {
        await axios.put(`${API}/categories/${editingCategory.id}`, formData);
        toast.success('Category updated');
      } else {
        await axios.post(`${API}/categories`, formData);
        toast.success('Category created');
      }
      setOpen(false);
      setEditingCategory(null);
      setFormData({ name: '', category_type: 'expense', color: '#5C745A' });
      loadCategories();
    } catch (err) {
      toast.error('Failed to save category');
      console.error(err);
    }
  };

  const handleDelete = async (id, isDefault) => {
    if (isDefault) {
      toast.error('Cannot delete default category');
      return;
    }
    if (!window.confirm('Delete this category?')) return;
    try {
      await axios.delete(`${API}/categories/${id}`);
      toast.success('Category deleted');
      loadCategories();
    } catch (err) {
      toast.error('Failed to delete category');
      console.error(err);
    }
  };

  const handleEdit = (category) => {
    setEditingCategory(category);
    setFormData({
      name: category.name,
      category_type: category.category_type,
      color: category.color
    });
    setOpen(true);
  };

  const incomeCategories = categories.filter(c => c.category_type === 'income');
  const expenseCategories = categories.filter(c => c.category_type === 'expense');

  const colorOptions = [
    { value: '#5C745A', label: 'Moss Green' },
    { value: '#C06B52', label: 'Terracotta' },
    { value: '#D4A373', label: 'Sand' },
    { value: '#7CA1A6', label: 'Teal' },
    { value: '#78716C', label: 'Stone' },
    { value: '#A8A29E', label: 'Gray' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-heading text-3xl tracking-tight" style={{ fontFamily: 'Manrope, sans-serif', color: '#1C1917' }}>
            Categories
          </h2>
          <p className="text-sm mt-1" style={{ color: '#78716C' }}>Customize your transaction categories</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button 
              data-testid="add-category-btn"
              className="bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg"
              onClick={() => {
                setEditingCategory(null);
                setFormData({ name: '', category_type: 'expense', color: '#5C745A' });
              }}
            >
              <Plus size={18} className="mr-2" />
              Add Category
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingCategory ? 'Edit Category' : 'Add Category'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>Category Name</Label>
                <Input
                  data-testid="category-name-input"
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  placeholder="e.g., Coffee & Tea"
                  required
                />
              </div>
              <div>
                <Label>Type</Label>
                <Select value={formData.category_type} onValueChange={val => setFormData({...formData, category_type: val})}>
                  <SelectTrigger data-testid="category-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="income">Income</SelectItem>
                    <SelectItem value="expense">Expense</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Color</Label>
                <div className="flex gap-2 flex-wrap mt-2">
                  {colorOptions.map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setFormData({...formData, color: opt.value})}
                      className={`w-10 h-10 rounded-lg border-2 transition-all duration-200 ${
                        formData.color === opt.value ? 'border-[#1C1917] scale-110' : 'border-[#E5E2DC]'
                      }`}
                      style={{ backgroundColor: opt.value }}
                      title={opt.label}
                    />
                  ))}
                </div>
              </div>
              <Button type="submit" data-testid="save-category-btn" className="w-full bg-[#5C745A] text-white hover:bg-[#475F45] rounded-lg">
                {editingCategory ? 'Update' : 'Create'} Category
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Income Categories */}
      <div>
        <h3 className="font-heading text-xl mb-4" style={{ color: '#5C745A' }}>Income Categories</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {incomeCategories.map(cat => (
            <div 
              key={cat.id}
              data-testid={`category-${cat.id}`}
              className="bg-white border border-[#E5E2DC] rounded-lg p-4 flex items-center justify-between hover:-translate-y-1 hover:shadow-lg transition-all duration-200"
            >
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: cat.color }} />
                <div>
                  <div className="font-medium" style={{ color: '#1C1917' }}>{cat.name}</div>
                  {cat.is_default && (
                    <span className="text-xs" style={{ color: '#78716C' }}>Default</span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleEdit(cat)}
                  data-testid={`edit-category-${cat.id}`}
                  className="text-[#5C745A] hover:text-[#475F45] transition-colors duration-200"
                >
                  <Pencil size={16} />
                </button>
                {!cat.is_default && (
                  <button
                    onClick={() => handleDelete(cat.id, cat.is_default)}
                    data-testid={`delete-category-${cat.id}`}
                    className="text-[#C06B52] hover:text-[#A35943] transition-colors duration-200"
                  >
                    <Trash size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Expense Categories */}
      <div>
        <h3 className="font-heading text-xl mb-4" style={{ color: '#C06B52' }}>Expense Categories</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {expenseCategories.map(cat => (
            <div 
              key={cat.id}
              data-testid={`category-${cat.id}`}
              className="bg-white border border-[#E5E2DC] rounded-lg p-4 flex items-center justify-between hover:-translate-y-1 hover:shadow-lg transition-all duration-200"
            >
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: cat.color }} />
                <div>
                  <div className="font-medium" style={{ color: '#1C1917' }}>{cat.name}</div>
                  {cat.is_default && (
                    <span className="text-xs" style={{ color: '#78716C' }}>Default</span>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleEdit(cat)}
                  data-testid={`edit-category-${cat.id}`}
                  className="text-[#5C745A] hover:text-[#475F45] transition-colors duration-200"
                >
                  <Pencil size={16} />
                </button>
                {!cat.is_default && (
                  <button
                    onClick={() => handleDelete(cat.id, cat.is_default)}
                    data-testid={`delete-category-${cat.id}`}
                    className="text-[#C06B52] hover:text-[#A35943] transition-colors duration-200"
                  >
                    <Trash size={16} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Categories;
