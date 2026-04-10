from django.urls import path
from . import views

urlpatterns = [
    path('', views.browse, name='browse'),
    path('producers/', views.producers, name='producers'),
    path('add-product/', views.add_product, name='add_product'),
    path('my-products/', views.my_products, name='my_products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    
    # Recipe URLs
    path('recipes/', views.browse_recipes, name='browse_recipes'),
    path('my-recipes/', views.my_recipes, name='my_recipes'),
    path('favorite-recipes/', views.my_favorite_recipes, name='my_favorite_recipes'),
    path('add-recipe/', views.add_recipe, name='add_recipe'),
    path('recipe/<int:recipe_id>/', views.recipe_detail, name='recipe_detail'),
    path('recipe/<int:recipe_id>/edit/', views.edit_recipe, name='edit_recipe'),
    path('recipe/<int:recipe_id>/delete/', views.delete_recipe, name='delete_recipe'),
    path('recipe/<int:recipe_id>/toggle-favorite/', views.toggle_favorite_recipe, name='toggle_favorite_recipe'),
    
    # Farm Story URLs
    path('stories/', views.browse_stories, name='browse_stories'),
    path('my-stories/', views.my_stories, name='my_stories'),
    path('add-story/', views.add_story, name='add_story'),
    path('story/<int:story_id>/', views.story_detail, name='story_detail'),
    path('story/<int:story_id>/edit/', views.edit_story, name='edit_story'),
    path('story/<int:story_id>/delete/', views.delete_story, name='delete_story'),
    
    # Producer Profile
    path('producer/<int:producer_id>/', views.producer_profile, name='producer_profile'),
    
    # Product Review URLs
    path('product/<int:product_id>/review/', views.submit_review, name='submit_review'),
    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('review/<int:review_id>/respond/', views.producer_respond_review, name='producer_respond_review'),
    path('my-reviews/', views.my_reviews, name='my_reviews'),
]
